/*****************************************************************************
 * Project: RooFit                                                           *
 * Package: RooFitModels                                                     *
 *    File: $Id$
 * Authors:                                                                  *
 *   DMS, Diego Martinez Santos, Nikhef, Diego.Martinez.Santos@cern.ch       *
 *                                                                           *
 * Copyright (c) 2013, Nikhef. All rights reserved.                          *
 *                                                                           *
 * Redistribution and use in source and binary forms,                        *
 * with or without modification, are permitted according to the terms        *
 * listed in LICENSE (http://roofit.sourceforge.net/license.txt)             *
 *****************************************************************************/

#include "TMath.h"

#include "RooIpatia2.h"
#include "RooIpatiaHelpers.h"


ClassImp(RooIpatia2)

RooIpatia2::RooIpatia2(const char *name, const char *title,
                       RooAbsReal& _x,
                       RooAbsReal& _l,
                       RooAbsReal& _zeta,
                       RooAbsReal& _fb,
                       RooAbsReal& _sigma,
                       RooAbsReal& _mu,
                       RooAbsReal& _a,
                       RooAbsReal& _n,
                       RooAbsReal& _a2,
                       RooAbsReal& _n2) :
  RooAbsPdf(name,title),
  x("x","x",this,_x),
  l("l","l",this,_l),
  zeta("zeta","zeta",this,_zeta),
  fb("fb","fb",this,_fb),
  sigma("sigma","sigma",this,_sigma),
  mu("mu","mu",this,_mu),
  a("a","a",this,_a),
  n("n","n",this,_n),
  a2("a2","a2",this,_a2),
  n2("n2","n2",this,_n2)
{
}


RooIpatia2::RooIpatia2(const RooIpatia2& other, const char* name) :
  RooAbsPdf(other,name),
  x("x",this,other.x),
  l("l",this,other.l),
  zeta("zeta",this,other.zeta),
  fb("fb",this,other.fb),
  sigma("sigma",this,other.sigma),
  mu("mu",this,other.mu),
  a("a",this,other.a),
  n("n",this,other.n),
  a2("a2",this,other.a2),
  n2("n2",this,other.n2)
{
}



Double_t RooIpatia2::evaluate() const
{
  Double_t d = x-mu;
  Double_t cons0 = TMath::Sqrt(zeta);
  Double_t alpha, beta, delta,  cons1, phi, A, B, k1, k2;
  Double_t asigma = a*sigma;
  Double_t a2sigma = a2*sigma;
  Double_t out = 0.;
  if (zeta!= 0.) {
    phi = BK(l+1.,zeta)/BK(l,zeta); // careful if zeta -> 0. You can implement a function for the ratio, but carefull again that |nu + 1 | != |nu| + 1 so you jave to deal wiht the signs
    cons1 = sigma/TMath::Sqrt(phi);
    alpha  = cons0/cons1;//*TMath::Sqrt((1 - fb*fb));
    beta = fb;//*alpha;
    delta = cons0*cons1;

    if (d < -asigma){
      //printf("-_-\n");
      //printf("alpha %e\n",alpha);
      //printf("beta %e\n",beta);
      //printf("delta %e\n",delta);

      k1 = LogEval(-asigma,l,alpha,beta,delta);
      k2 = diff_eval(-asigma,l,alpha,beta,delta);
      B = -asigma + n*k1/k2;
      A = k1*TMath::Power(B+asigma,n);
      //printf("k1 is %e\n",k1);
      //printf("k2 is %e\n",k2);
      //printf("A is%e\n",A);
      //printf("B is%e\n",B);
      out = A*TMath::Power(B-d,-n);
    }
    else if (d>a2sigma) {
      //printf("uoeo\n");
      k1 = LogEval(a2sigma,l,alpha,beta,delta);
      k2 = diff_eval(a2sigma,l,alpha,beta,delta);

      B = -a2sigma - n2*k1/k2;

      A = k1*TMath::Power(B+a2sigma,n2);

      out =  A*TMath::Power(B+d,-n2);

    }
    else {
      //printf("HERE\n");
      out = LogEval(d,l,alpha,beta,delta);
    }



  }
  else if (l < 0.) {
    beta = fb;
    cons1 = -2.*l;
    delta = sigma;
    if (d < -asigma ) {
      cons1 = TMath::Exp(-beta*asigma);
      phi = 1. + a*a;
      k1 = cons1*TMath::Power(phi,l-0.5);
      k2 = beta*k1- cons1*(l-0.5)*TMath::Power(phi,l-1.5)*2*a/delta;
      B = -asigma + n*k1/k2;
      A = k1*TMath::Power(B+asigma,n);
      out = A*TMath::Power(B-d,-n);
    }
    else if (d > a2sigma) {
      cons1 = TMath::Exp(beta*a2sigma);
      phi = 1. + a2*a2;
      k1 = cons1*TMath::Power(phi,l-0.5);
      k2 = beta*k1+ cons1*(l-0.5)*TMath::Power(phi,l-1.5)*2.*a2/delta;
      B = -a2sigma - n2*k1/k2;
      A = k1*TMath::Power(B+a2sigma,n2);
      out =  A*TMath::Power(B+d,-n2);

    }
    else { out = TMath::Exp(beta*d)*TMath::Power(1. + d*d/(delta*delta),l-0.5);}
  }
  else {
    //printf("zeta = 0 only suported for l < 0, while l = %e\n",0);
  }
  //printf("result is %e\n",out);
  return out;
}
